// case38: 全局单例模式测试
// 测试单例对象在多线程环境下的竞争

class Singleton {
    private static var instance: ?Singleton = None
    public var counter: Int64 = 0
    
    public static func getInstance(): Singleton {
        if (instance == None) {
            instance = Singleton()
        }
        return instance!
    }
}

main() {
    spawn {
        let s = Singleton.getInstance()
        s.counter = s.counter + 1  // 写操作
    }
    
    spawn {
        let s = Singleton.getInstance()
        s.counter = s.counter + 2  // 写操作
    }
}