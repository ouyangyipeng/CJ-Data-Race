// 测试用例25: 静态变量竞争
// 测试静态变量的数据竞争

class Counter {
    static var count: Int64 = 0
}

main() {
    // 线程1: 写入静态变量
    spawn {
        Counter.count = Counter.count + 1  // 写操作
    }
    
    // 线程2: 读取静态变量
    spawn {
        println(Counter.count)  // 读操作
    }
    
    // 线程3: 写入静态变量
    spawn {
        Counter.count = Counter.count + 1  // 写操作
    }
    
    println(Counter.count)
}