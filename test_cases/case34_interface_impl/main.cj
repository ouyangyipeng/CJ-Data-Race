// case34: 接口实现竞争测试
// 测试通过接口访问共享变量的场景

interface ICounter {
    func increment(): Unit
    func getValue(): Int64
}

class Counter: ICounter {
    private var value: Int64 = 0
    
    public func increment(): Unit {
        value = value + 1
    }
    
    public func getValue(): Int64 {
        return value
    }
}

main() {
    let counter = Counter()
    
    spawn {
        counter.increment()  // 写操作
    }
    
    spawn {
        counter.increment()  // 写操作
    }
}