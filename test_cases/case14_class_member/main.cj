// 测试用例14: 类成员访问竞争
// 多线程访问同一对象的成员变量

class Counter {
    public var value: Int64 = 0
}

main() {
    let counter = Counter()
    
    // 线程1: 写成员变量
    spawn {
        counter.value = counter.value + 1  // 写操作
    }
    
    // 线程2: 读成员变量
    spawn {
        let v = counter.value  // 读操作，存在RW竞争
        println(v)
    }
    
    println(counter.value)
}